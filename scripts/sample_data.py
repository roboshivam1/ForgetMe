from shared.models import Account, Breach

SAMPLE_ACCOUNTS = [
    Account(
        service="LinkedIn", domain="linkedin.com",
        breach=Breach(name="LinkedIn", domain="linkedin.com", breach_date="2012-05-05",
                      data_classes=["Email addresses", "Passwords"], pwn_count=164611595),
    ),
    Account(
        service="Dropbox", domain="dropbox.com",
        breach=Breach(name="Dropbox", domain="dropbox.com", breach_date="2012-07-01",
                      data_classes=["Email addresses", "Passwords"], pwn_count=68648009),
    ),
    Account(
        service="Canva", domain="canva.com",
        breach=Breach(name="Canva", domain="canva.com", breach_date="2019-05-24",
                      data_classes=["Email addresses", "Names", "Passwords", "Usernames"], pwn_count=137272116),
    ),
    Account(
        service="Spotify", domain="spotify.com",
        breach=Breach(name="Spotify", domain="spotify.com", breach_date="2020-11-01",
                      data_classes=["Email addresses"], pwn_count=350000),
    ),
    Account(
        service="RecentShop", domain="recentshop.example",
        breach=Breach(name="RecentShop", domain="recentshop.example", breach_date="2025-06-01",
                      data_classes=["Email addresses", "Passwords", "Phone numbers"], pwn_count=900000),
    ),
    Account(
        service="QuickLoan", domain="quickloan.example",
        breach=Breach(name="QuickLoan", domain="quickloan.example", breach_date="2025-03-01",
                      data_classes=["Email addresses", "Passwords", "Bank account numbers"], pwn_count=400000),
    ),
    Account(service="Swiggy", domain="swiggy.com", source="inbox"),
]
