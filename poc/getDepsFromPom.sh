
function usage(){
		echo "Usage: getDeps [-v] aar|jar"
}
if [ $# -lt 1 ]; then
		usage
		exit 1
fi
while [ "$1" != "" ]; do
    case $1 in
        -v | --verbose )    	
				verbose=1                
				;;
        -h | --help )           
				usage
                exit
                ;;
        * )
				aar_file=$1
				shift
				if [ "$1" != "" ]; then
						usage
						exit 1
				fi

    esac
    shift
done
pom=${aar_file%.*}.pom
groupIds=$(sed -n  "/\<groupId\>/s/\(<groupId>\)\(.*\)\(<\/groupId>\)/\2/p" $pom | sed '$!N; /^\(.*\)\n\1$/!P; D')
pass=true;
printed=""
for i in $groupIds
do
		if [ $pass ];then
				pass=
				continue
		fi
		printed="$printed $i"
		echo $i
done
