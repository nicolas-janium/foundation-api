for func_folder in ./functions/*/
do
    folder_name="${func_folder%"${func_folder##*[!/]}"}"
    folder_name="${folder_name##*/}"

    func_name="${folder_name//_/-}"

    echo "Adding the trigger url for ${func_name} to env files..."
    echo "${folder_name^^}_URL: https://${1}-${3}.cloudfunctions.net/${func_name}" >> ./functions/envs.yaml
    echo "${folder_name^^}_URL=https://${1}-${3}.cloudfunctions.net/${func_name}" >> .env
    # echo `gcloud functions describe ${func_name} --region=${1} --format=json` > ${func_folder}/describe.json
done


for func_folder in ./functions/*/
do
    folder_name="${func_folder%"${func_folder##*[!/]}"}"
    folder_name="${folder_name##*/}"

    func_name="${folder_name//_/-}"

    echo "Deploying ${func_name} function..."

    if [ "${func_name}" == 'process-contact-source-task-handler' ]
    then
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2} --memory=1024MB --max-instances=1000 &
    elif [ "${func_name}" == 'parse-email-function' ]
    then
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2} --memory=512MB --max-instances=1000 &
    elif [ "${func_name}" == 'error-notifier-function' ]
    then
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-topic=janium-logging-topic --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2} --memory=512MB --max-instances=1000 &

    else
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2} --max-instances=1000 &
    fi

    # echo "Adding IAM policy binding for ${func_name} function..."
    # gcloud functions add-iam-policy-binding ${func_name} --member=allUsers --region=${1} --role=roles/cloudfunctions.invoker
done

wait