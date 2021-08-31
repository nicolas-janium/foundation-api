for func_folder in ./functions/*/
do
    folder_name="${func_folder%"${func_folder##*[!/]}"}"
    folder_name="${folder_name##*/}"
    func_name="${folder_name}_task_handler"
    func_name="${func_name//_/-}"
    trigger_url=`jq .httpsTrigger.url ${func_folder}/describe.json`
    trigger_url1="${folder_name^^}_TRIGGER_URL=${trigger_url}"
    trigger_url2="${folder_name^^}_TRIGGER_URL: ${trigger_url}"
    echo ${trigger_url1} | tr -d '"' >> .env
    echo ${trigger_url2} | tr -d '"' >> ./functions/envs.yaml
done