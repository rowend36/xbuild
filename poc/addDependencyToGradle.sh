if  [ -z $1 ] || [ $1 = "--help" ] || [ $1 = "-h" ] ;then
		echo "addDeps2Gradle depname gradlefile"
fi
sed "/dependencies/a\ \ \ \ compile project(\":$1\")" $2
