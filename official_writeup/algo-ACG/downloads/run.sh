# Script for downloading animal images.
# You need to follow the instructions in `page.html`.
# Once you got the image links correct, remove the `tee` at the end and uncomment the `aria2c` to download.
grep -hoP 'https://(images|plus)\.unsplash\.com/(premium_)?photo[^"?]*' page*.html | sort | uniq | sed 's/$/?w=512/' | tee >(wc -l) \
	# | aria2c -j 20 -i - -c  # remove the tee and uncomment this line to download
