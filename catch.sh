read IN # This reads a string from stdin and stores it in a variable called IN
string="Conflicting migrations detected; multiple leaf nodes in the migration graph:"
echo 'TESTING'
echo $IN
if [[ $IN =~ $string ]]; then
    echo "BASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASH1"
    echo $IN
    echo $string

    set -e
fi
echo "BASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASHBASH0"
