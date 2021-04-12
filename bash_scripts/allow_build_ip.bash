ip=$(curl ifconfig.me)

gcloud sql instances patch $1 --authorized-networks="67.176.4.32","${ip}"