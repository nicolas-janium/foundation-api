for file in ./functions/*/requirements.txt
do
    cat ./requirements.txt > $file
done