#!/bin/bash

API_HOST="exercisedb.p.rapidapi.com"
API_KEY="172aebe54amshfdaa6eb3183bfd0p16dcd1jsn6dca19e7e9c3"
BASE_URL="https://$API_HOST/exercises/bodyPart"

body_parts=("back" "cardio" "chest" "lower arms" "lower legs" "neck" "shoulders" "upper arms" "upper legs" "waist")

for part in "${body_parts[@]}"; do
    encoded_part=$(echo "$part" | sed 's/ /%20/g') # Encode spaces for URLs
    response=$(curl --silent --request GET \
        --url "$BASE_URL/$encoded_part?limit=1" \
        --header "x-rapidapi-host: $API_HOST" \
        --header "x-rapidapi-key: $API_KEY")

    echo "$part: $response"
done
