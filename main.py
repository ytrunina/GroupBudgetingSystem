from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import mysql.connector
import hashlib

app = Flask(__name__, static_url_path='/static')
app.config["SESSION_TYPE"] = "filesystem"
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

app.secret_key = 'your_secret_key'
Session(app)

env = Environment(loader=FileSystemLoader('templates'))

mydb = mysql.connector.connect(
    host="db-vaqay.c50qqk98cxr9.us-east-1.rds.amazonaws.com",
    user="nick",
    password="Welcome123!",
    database="vaqay_test"
)


@app.route('/')
def landing():
    if session.get('username'):
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username'):
        return redirect(url_for('login'))

    # if user is logged in, get their budgets
    user_id = session.get('id')
    with mydb.cursor() as cur:
        # funky join stuff
        # take me to funky town
        cur.execute("SELECT b.budgetName, b.budgetTypeId, b.id FROM Budgets b JOIN BudgetUsers bu ON b.Id = bu.budgetId WHERE bu.userId = %s", 
                    (user_id,))
        budgets = cur.fetchall()
        print(budgets)
        cur.close()
        return render_template('dashboard.html', budgets=budgets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    cur = mydb.cursor()
    cur.execute("SELECT * FROM Users")
    for entry in cur:
        print(entry)

    cur.close()

    if request.method == 'POST':
        uname = request.form.get('username')
        pword = request.form.get('password')

        pword = hashlib.sha256(pword.encode()).hexdigest()

        try:
            print("trying")
            cur = mydb.cursor()
            cur.execute(
                "SELECT id FROM Users WHERE password = %s AND username = %s", (pword, uname))

            u_id = cur.fetchone()[0]

            if not u_id:
                raise Exception("User not found!")

            session['username'] = uname
            session['id'] = int(u_id)

            session.permanent = False

            return redirect(url_for('dashboard'))
        except:
            print("excepting")
            return render_template('login.html', result_msg='Login failed!', failed=True)
        finally:
            print("finally")
            cur.close()

    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('id', None)
    session.pop('current_budget_id', None)
    return redirect(url_for('landing'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form.get('regusername')
        pword = request.form.get('regpassword')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = "hello@hello.com"
        phone = request.form.get('phone')

        pword = hashlib.sha256(pword.encode()).hexdigest()

        # check if username is already taken
        cur = mydb.cursor()
        cur.execute("SELECT username FROM Users WHERE username = %s", (uname,))
        if cur.fetchone():
            return render_template('register.html', exception='User already exists!', failed=True)
        if not uname:
            return render_template('register.html', exception='Username cannot be empty!', failed=True)
        elif not pword:
            return render_template('register.html', exception='Password cannot be empty!', failed=True)
        else:
            try:
                cur = mydb.cursor()

                """
                insert the new user into the database
                this is a stored procedure call which adds a user to the Users table
                then at adds the user's details to the UserDetails table
                """
                cur.execute("CALL CreateUser (%s, %s, %s, %s, %s, %s)",
                            (uname, pword, first_name, last_name, email, phone))

                mydb.commit()

                flash("User created successfully!")
                return redirect(url_for('login'))
            except:
                # if exception, roll back
                mydb.rollback()

                flash("User creation failed!")
                return redirect(url_for('register'))
            finally:
                cur.close()
    else:
        return render_template('register.html')

@app.route('/add_budget', methods=['POST'])
def add_budget():
    # get form data and store in variables
    budget_name = request.form.get('name')
    budget_type = request.form.get('b_type')

    # get the user id and password from the session
    user_id = session.get('id')
    username = session.get('username')

    with mydb.cursor() as cur:
        try:
            # try to insert the budget into the database
            cur.execute("INSERT INTO Budgets (userID, budgetTypeID, budgetName, auditUser) VALUES (%s, %s, %s, %s)",
                        (user_id, budget_type, budget_name, username))
            mydb.commit()

            budget_id = cur.lastrowid

            cur.execute("INSERT INTO BudgetUsers (budgetID, userID, auditUser) VALUES (%s, %s, %s)",
                        (budget_id, user_id, username))
            mydb.commit()
        except:
            # if exception, roll back
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('dashboard'))

@app.route('/edit_budget', methods=['POST'])
def edit_budget():
    with mydb.cursor() as cur:
        # get form data and store in variables
        budget_name = request.form.get('name')
        budget_type = request.form.get('b_type')
        budget_id = request.form.get('budget_id')

        # get the user id and password from the session
        username = session.get('username')

        with mydb.cursor() as cur:
            try:
                # try to insert the budget into the database
                cur.execute("UPDATE Budgets SET budgetTypeID = %s, budgetName = %s, auditUser = %s WHERE id = %s",
                            (budget_type, budget_name, username, budget_id))

                mydb.commit()
                print("budget edit succeeded")
            except Exception as e:
                # if exception, roll back
                print("budget edit failed: ", e)
                mydb.rollback()
            finally:
                cur.close()
                return redirect(url_for('dashboard'))

@app.route('/delete_budget', methods=['POST'])
def delete_budget():
    # get the budget id from the form
    budget_id = request.form.get('budget_id')
    print("budget id: " + budget_id)
    with mydb.cursor() as cur:
        try:
            # try to delete the budget from the database
            cur.execute("DELETE FROM BudgetUsers WHERE budgetID = %s", (budget_id,))
            cur.execute("DELETE FROM Transactions WHERE budgetID = %s", (budget_id,))
            cur.execute("DELETE FROM Budgets WHERE id = %s", (budget_id,))
            mydb.commit()
            print("you succeeded")
        except Exception as e:
            print("you fucked up: ", e)
            # if exception, roll back
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('dashboard'))

@app.route('/budget_overview', methods=['GET', 'POST'])
def budget_overview():
    # get the budget id from the form
    budget_id = request.form.get('budget_id')
    if budget_id is not None:
        session['current_budget_id'] = budget_id
    else:
        budget_id = session['current_budget_id']
    with mydb.cursor() as cur:
        cur.execute("SELECT budgetName FROM Budgets WHERE id = %s", (budget_id,))
        budget_name = cur.fetchone()[0]
        print("budget id: ", budget_id)
        
        cur.execute("SELECT budgetTypeId from Budgets WHERE id = %s", (budget_id,))
        budget_type = cur.fetchone()[0]

        # get all the common categories
        cur.execute("SELECT id, description FROM CommonCategories")

        categories = cur.fetchall()
        # print("common categories: ", categories)

        # Create a dictionary to map commonCategoryId to description
        category_dict = {}
        for category_id, description in categories:
            category_dict[category_id] = description

        # get all transactions related to the budget
        cur.execute("SELECT commonCategoryId, description, date, amount, id FROM Transactions WHERE budgetId = %s", (budget_id,))

        # make a tuple from the query
        transactions = cur.fetchall()

        for i in range(len(transactions)):
            category_id = transactions[i][0]
            description = category_dict.get(category_id)
            transactions[i] = (description,) + transactions[i][1:]

        cur.close()
        return render_template('transactions.html', budget_name = budget_name, budget_type = budget_type, transactions = transactions, categories = categories)
    
@app.route('/visualize_budget')
def visualize_budget():
    with mydb.cursor() as cur:
        try:
            cur.execute("SELECT id, description FROM CommonCategories")

            categories = cur.fetchall()
            # print("common categories: ", categories)

            # Create a dictionary to map commonCategoryId to description
            category_dict = {}
            for category_id, description in categories:
                category_dict[category_id] = description
            budget_id = session['current_budget_id']
            cur.execute("SELECT commonCategoryId, amount FROM Transactions WHERE budgetId = %s", (budget_id,))

            transactions = cur.fetchall()

            for i in range(len(transactions)):
                category_id = transactions[i][0]
                description = category_dict.get(category_id)
                transactions[i] = (description,) + transactions[i][1:]

            print("transactions: ", transactions)

            data = {'labels': [], 'values': []}
            for category, amount in transactions:
                if category:
                    if category in data['labels']:
                        data['values'][data['labels'].index(category)] += float(amount)
                    else:
                        data['labels'].append(category)
                        data['values'].append(float(amount))

            print("data: ", data)
        except Exception as e:
            print("error visualizing data: ", e)
        finally:
            cur.close()
            return jsonify(data)
    
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    # get form data and store in variables
    category_id = request.form.get('transactionCategory')
    description = request.form.get('transactionDescription')
    date = request.form.get('transactionDate')
    amount = request.form.get('transactionAmount')
    budget_id = session.get('current_budget_id')
    user_id = session.get('id')

    # get the username from the session
    username = session.get('username')

    with mydb.cursor() as cur:
        try:
            # try to insert the budget into the database
            print("trying")
            cur.execute("INSERT INTO Transactions (userId, budgetID, commonCategoryId, description, date, amount, auditUser) VALUES (%s, %s, %s, %s, %s, %s, %s)", (user_id, budget_id, category_id, description, date, amount, username))
            mydb.commit()
        except Exception as e:
            print("excepting: ", e)
            # if exception, roll back
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('budget_overview'))
        
@app.route('/delete_transaction', methods=['POST'])
def delete_transaction():
    print("delete called")
    print("transaction id: ", request.form.get('transaction_id'))

    with mydb.cursor() as cur:
        try:
            cur.execute("DELETE FROM Transactions WHERE id = %s", (request.form.get('transaction_id'),))
            mydb.commit()
        except Exception as e:
            print("delete failed: ", e)
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('budget_overview'))
        
@app.route('/add_user_to_budget', methods=['POST'])
def add_user_to_budget():
    print("add user to budget called")
    budget_id = session.get('current_budget_id')
    username = request.form.get('username')

    with mydb.cursor() as cur:
        try:
            cur.execute("SELECT id FROM Users WHERE username = %s", (username,))
            user_id = cur.fetchone()[0]
            if user_id == None:
                raise Exception("user not found")
            
            cur.execute("SELECT id FROM BudgetUsers WHERE budgetId = %s AND userId = %s", (budget_id, user_id))
            if cur.fetchone() != None:
                raise Exception("user already in budget")

            cur.execute("INSERT INTO BudgetUsers (budgetId, userId, auditUser) VALUES (%s, %s, %s)", (budget_id, user_id, session.get('username')))
            mydb.commit()
        except Exception as e:
            print("add user to budget failed: ", e)
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('budget_overview'))

@app.route('/profile', methods=['GET'])
def profile():
    user_id = session.get('id')
    cur = mydb.cursor()
    cur.execute(
        "SELECT firstName, lastName, email, phoneNumber FROM UserDetails WHERE userID = %s", (user_id,))
    first_name, last_name, email, phone = cur.fetchone()
    return render_template('profile.html', first_name=first_name, last_name=last_name, email=email, phone=phone)


@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    with mydb.cursor() as cur:
        try:
            user_id = session.get('id')
            user_data = (request.form.get('firstName'), request.form.get(
                'lastName'), request.form.get('regemail'), request.form.get('phone'))

            cur.execute("UPDATE UserDetails SET firstName = %s, lastName = %s, email = %s, phoneNumber = %s WHERE userId = %s",
                        (user_data[0], user_data[1], user_data[2], user_data[3], user_id))

            mydb.commit()
        except:
            print("edit profile failed")
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('profile'))


@app.route('/change_password', methods=['POST'])
def change_password():
    with mydb.cursor() as cur:
        try:
            user_id = session.get('id')
            new_pword = request.form.get('regpassword')
            new_pword = hashlib.sha256(new_pword.encode()).hexdigest()

            cur.execute(
                "UPDATE Users SET password = %s WHERE id = %s", (new_pword, user_id))

            mydb.commit()
        except:
            print("change password failed")
            mydb.rollback()
        finally:
            cur.close()
            return redirect(url_for('profile'))


if __name__ == '__main__':
    app.run()
