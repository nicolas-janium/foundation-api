echo "FLASK_APP=foundation_api" > .env
echo "FLASK_ENV=production" >> .env

# echo "IS_BUILD=1" >> .env

echo "DB_USER=$1" >> .env
echo "DB_PASSWORD=$2" >> .env
echo "DB_HOST=$3" >> .env
echo "DB_PUBLIC_HOST=$4" >> .env
echo "DB_NAME=$5" >> .env
echo "SENDGRID_API_KEY=$6" >> .env
echo "PROJECT_ID=$7" >> .env
echo "JANIUM_EMAIL_ID=7cb8e90c-2c64-4e48-ba0f-afe6405bec04" >> .env
echo "SES_ACCESS_KEY_ID=$8" >> .env
echo "SES_SECRET_ACCESS_KEY=$9" >> .env
echo "TESTING_DB_USER=$1" >> .env
echo "TESTING_DB_PASSWORD=$2" >> .env
echo "TESTING_DB_PRIVATE_HOST=$3" >> .env
echo "TESTING_DB_PUBLIC_HOST=$4" >> .env
echo "TESTING_DB_DATABASE=testing_db" >> .env
echo "TASK_QUEUE_LOCATION=${10}" >> .env
echo "APP_SECRET_KEY=${11}" >> .env