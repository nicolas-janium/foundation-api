for func_folder in ./functions/*/
do
    folder_name="${func_folder%"${func_folder##*[!/]}"}"
    folder_name="${folder_name##*/}"
    func_name="${folder_name}_task_handler"
    func_name="${func_name//_/-}"
    trigger_url=`jq .httpsTrigger.url ${func_folder}/describe.json`
    echo "${folder_name^^}_TRIGGER_URL=${trigger_url}" | tr -d '"' >> .env
done