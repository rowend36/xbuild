function usage(){
		echo "Usage: aar2lib [-v] [-d dest] aar"
}
if [ $# -lt 1 ]; then
		usage
		exit 1
fi
while [ "$1" != "" ]; do
    case $1 in
        -d | --dest )
				shift
				dest=$(realpath $1)
                ;;
        -v | --verbose )    	
				verbose=1                
				;;
        -h | --help )           
				usage
                exit
                ;;
        * )
				aar_file=$1
				if [ -z $dest ]; then
						dest=$(dirname $(realpath "${aar_file}"))/exploded/$(basename "${aar_file}")-exploded
				fi
				shift
				if [ "$1" != "" ]; then
						usage
						exit 1
				fi

    esac
    shift
done
lastdir=$(pwd)
mypath=~/system/src/scripts/
if [ ! -f $aar_file ]; then
		echo "No such file $aar_file";
		exit 1
fi
test -d $dest || mkdir -p $dest;
aar_file_path=$(realpath "$aar_file")
cd $dest;
unzip $aar_file_path;
test $? == 0 || (echo "Aar failed" && exit 1);
test -d libs || mkdir libs
test -d src/main || mkdir -p src/main
mv res src/main
PACKAGE_NAME=$(source ${mypath}/getPackageName.sh AndroidManifest.xml)
source $mypath/createGradle.sh $PACKAGE_NAME> build.gradle
mv AndroidManifest.xml src/main
mv classes.jar libs/
DEPENDENCIES=$(bash $mypath/getDepsFromPom.sh $aar_file_path);
for i in $DEPENDENCIES;
do
		echo $i;
		(bash $mypath/addDependencyToGradle.sh $i build.gradle)>$mypath/log.txt;
		mv $mypath/log.txt build.gradle;
done
cd ..
mv $dest $PACKAGE_NAME;
cd $lastdir;
