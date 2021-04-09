echo "FLASK_APP=foundation_api" > .env
echo "FLASK_ENV=production" >> .env
echo "DB_USER=$1" >> .env
echo "DB_PASSWORD=$2" >> .env
echo "DB_HOST=$3" >> .env
echo "DB_NAME=$4" >> .env
echo "SENDGRID_API_KEY=$5" >> .env
# echo "Hello from bash script $1"