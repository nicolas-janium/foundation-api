echo "FLASK_APP=foundation_api" > .env
echo "FLASK_ENV=production" >> .env

# echo "IS_BUILD=1" >> .env

echo "DB_USER=$1" >> .env
echo "DB_PASSWORD=$2" >> .env
echo "DB_HOST=$3" >> .env
echo "DB_PUBLIC_HOST=$4" >> .env
echo "DB_NAME=$5" >> .env
echo "SENDGRID_API_KEY=$6" >> .env