-- Yelena Trunina
-- This stored procedure gets all needed params and creates user entries on Users and UserDetails


create procedure CreateUser(IN p_username varchar(30), IN p_password varchar(100),
                                             IN p_firstName varchar(30),
                                             IN p_lastName varchar(30), IN p_email varchar(100),
                                             IN p_phoneNumber varchar(10))
BEGIN
  DECLARE p_userID INT;

  -- Check that all required input parameters have a value
  IF p_username IS NULL OR p_password IS NULL OR p_firstName IS NULL OR p_lastName IS NULL OR p_email IS NULL OR p_phoneNumber IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'All input parameters must have a value.';
  END IF;

  -- Insert new user into the Users table
  INSERT INTO Users (username, password)
  VALUES (p_username, p_password);

  -- Get the ID of the new user
  SET p_userID = LAST_INSERT_ID();

  -- Insert user details into the UserDetails table
  INSERT INTO UserDetails (userID, firstName, lastName, email, phoneNumber, auditUser)
  VALUES (p_userID, p_firstName, p_lastName, p_email, p_phoneNumber, p_username);
END;