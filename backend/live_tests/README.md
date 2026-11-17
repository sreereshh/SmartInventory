# Live tests (optional)

These run against a **running** server and a **freshly seeded** database (they create and change data).

```powershell
python manage.py runserver                       # terminal 1
python live_tests\api_and_web_live_test.py       # terminal 2 - HTTP checks of the web forms + REST API (no extra packages)
pip install playwright; playwright install chromium
python live_tests\ui_browser_test.py             # real Chromium browser test (52 checks), screenshots in live_tests\screenshots
```
Afterwards reset the data: delete `db.sqlite3`, then `python manage.py migrate` and `python manage.py seed_data`.
The normal automated suite (`python manage.py test`) needs none of this.
