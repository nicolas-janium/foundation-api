for func_folder in ./functions/*/
do
    folder_name="${func_folder%"${func_folder##*[!/]}"}"
    folder_name="${folder_name##*/}"
    func_name="${folder_name}_task_handler"
    func_name="${func_name//_/-}"
    echo "Deploying ${func_name} function..."
    gcloud functions deploy ${func_name} --region=${1} --entry-point=main --runtime=python38 --trigger-http --allow-unauthenticated --timeout=539 --env-vars-file=./functions/envs.yaml --source=${func_folder} --egress-settings=private-ranges-only --vpc-connector=${2}
    echo `gcloud functions describe ${func_name} --format=json` > ${func_folder}/describe.json
done