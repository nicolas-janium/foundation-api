for file in ./functions/*/model.py
do
    model=`cat ./foundation_api/V1/sa_db/model.py`
    echo "${model//db.Model/Base}" > $file
done