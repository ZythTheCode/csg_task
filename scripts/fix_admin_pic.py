import urllib.request

urls_to_test = [
    "https://res.cloudinary.com/rz2o4b1f/image/upload/v1/media/profile_pics/user_admin_f3f0883f_gkubg2",
    "https://res.cloudinary.com/rz2o4b1f/image/upload/v1/media/profile_pics/user_admin_f3f0883f_gkubg2.jpg",
    "https://res.cloudinary.com/rz2o4b1f/image/upload/v1/media/profile_pics/user_admin_f3f0883f_gkubg2.png",
    "https://res.cloudinary.com/rz2o4b1f/image/upload/v1/profile_pics/user_admin_f3f0883f_gkubg2",
    "https://res.cloudinary.com/rz2o4b1f/image/upload/v1/profile_pics/user_admin_f3f0883f_gkubg2.jpg",
    "https://res.cloudinary.com/rz2o4b1f/image/upload/v1/profile_pics/user_admin_f3f0883f_gkubg2.png",
]

with open("url_results.txt", "w", encoding="utf-8") as f:
    for url in urls_to_test:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=2)
            f.write(f"SUCCESS {resp.status} -> {url}\n")
        except Exception as e:
            f.write(f"FAILED ({e}) -> {url}\n")

print("Done")
