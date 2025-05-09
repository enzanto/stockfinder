echo "enter version number for stockfinder docker image"
echo "last version = v1.6.6"
read VERSION
script_path="$0"
full_path="$(cd "$(dirname "$script_path")" && pwd)/$(basename "$script_path")"
echo $full_path
echo "you have selected $VERSION"
if [ "$VERSION" = "development" ]; then
    echo "tagging build with $VERSION"
    docker buildx build --platform linux/amd64,linux/arm64  -t enzanto/stockfinder:$VERSION --push .
else
    echo "tagging build with latest,$VERSION"
    sed -i "0,/=/{s/=.*/= $VERSION\"/}" $full_path
    docker buildx build --platform linux/amd64,linux/arm64 -t enzanto/stockfinder -t enzanto/stockfinder:$VERSION --push .
fi
