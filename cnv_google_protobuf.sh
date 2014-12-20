# more info at http://python3porting.com/bookindex.html
# download protobuf-2.6.1.tar.gz for python
cd modules
rm -Rf google
tar -xzvf ~/Téléchargements/protobuf-2.6.1.tar.gz protobuf-2.6.1/google
2to3-3.4 protobuf-2.6.1/google -o google -W --no-diffs -p -n
rm -Rf protobuf-2.6.1
#find . -name '*.py' -type f -exec sed -i -e 's/except \([A-Za-z0-9_\.]*\), e/except \1 as e/g'  {} \;
