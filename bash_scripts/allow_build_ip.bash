if [ "$2" == "set" ]; then
    echo "Setting db server's authorized networks"
    ip=$(curl ifconfig.me)
    gcloud sql instances patch $1 --authorized-networks="67.176.4.32","${ip}"
else
    echo "Resetting db server's authorized networks"
    gcloud sql instances patch $1 --authorized-networks="67.176.4.32"
fi