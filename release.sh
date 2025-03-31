#!/bin/bash

baddeps=""
# check deps
python3 -m build.__init__ || baddeps="python3-build"
rpm -q twine || baddeps="${baddeps} twine"
if [ -n "${baddeps}" ]; then
    echo "${baddeps} must be installed!"
    exit 1
fi

if [ "$#" != "1" ]; then
    echo "Must pass release version!"
    exit 1
fi

version=$1
name=openqa_client
sed -i -e "s,version=\".*\",version=\"${version}\", g" setup.py
sed -i -e "s,version = \".*\",version = \"${version}\", g" pyproject.toml
sed -i -e "s,__version__ = \".*\",__version__ = \"${version}\", g" src/${name}/__init__.py
git add setup.py pyproject.toml src/${name}/__init__.py
git commit -s -m "Release ${version}"
git push
git tag -a -m "Release ${version}" ${version}
git push origin ${version}
python3 -m build .
twine upload -r pypi dist/${name}-${version}*
