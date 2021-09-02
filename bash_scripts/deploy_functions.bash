for func_folder in ./functions/*/
do
    folder_name="${func_folder%"${func_folder##*[!/]}"}"
    folder_name="${folder_name##*/}"

    if [ ${func_name} == 'parse_email' ]
    then
        func_name="${folder_name}_function"
    else
        func_name="${folder_name}_task_handler"
        func_name="${func_name//_/-}"
    fi

    echo "Deploying ${func_name} function..."

    if [ ${func_name} == 'process-contact-source-task-handler' ]
    then
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2} --memory=2048MB
    elif [ ${func_name} == 'parse-email-task-handler' ]
    then
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2} --memory=512MB
    else
        gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2}
    fi

    echo "Adding IAM policy binding for ${func_name} function..."
    gcloud functions add-iam-policy-binding ${func_name} --member=allUsers --region=${1} --role=roles/cloudfunctions.invoker

    echo "Adding the trigger url for ${func_name} function to describe.json file..."
    echo `gcloud functions describe ${func_name} --region=${1} --format=json` > ${func_folder}/describe.json
done