echo "FLASK_APP=foundation_api" > .flaskenv
echo "FLASK_ENV=production" >> .flaskenv
echo "DB_USER=$1" >> .flaskenv
echo "DB_PASSWORD=$2" >> .flaskenv
echo "DB_HOST=$3" >> .flaskenv
echo "DB_NAME=$4" >> .flaskenv
echo "SENDGRID_API_KEY=$5" >> .flaskenv
# echo "Hello from bash script $1"