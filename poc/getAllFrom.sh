#!$PREFIX/bin/bash
if [ $1 == "-h" ] || [ $1 == "--help" ] || [ -z $1 ];then
		echo "Usage: getAllFrom regex [directory]"
		echo "Get all the files that match a regex in a directory"
		exit;
fi
num=0
for i in $(find $2 | grep $1); do
		echo $i
		filename=$(basename $i)
		base=${filename%.*}
		ext=${filename##*.}
		if [ -d $i ];then
				continue
		else while [ -e $filename ]; do
				let num++
				filename=${base}-${num}.${ext}
		done
		fi
		num=0
		cp -i $i $filename;
done
