ip=$(curl ifconfig.me)

if [ "$4" == "setup" ]; then
    echo "\
    DROP DATABASE IF EXISTS testing_db;
    CREATE DATABASE testing_db;
    CREATE USER '$1'@'${ip}' IDENTIFIED BY '$3';
    GRANT ALL ON testing_db.* to '$1'@'${ip}';\
    " > ./testing_setup.sql
else
    echo "\
    DROP DATABASE IF EXISTS testing_db;
    DROP USER IF EXISTS '$1'@'${ip}';\
    " > ./testing_teardown.sql
fi 