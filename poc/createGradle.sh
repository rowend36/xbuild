sed -n  "/applicationId/s/\(applicationId \"\)\(.*\)\(\".*\)/\1${1}\3/ ;p" ~/system/src/scripts//temp.gradle
