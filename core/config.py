# app/core/config.py
# Yaha hum saari environment settings ek jagah define karte hain
# taaki poore project me bar bar os.environ.get() na likhna pade

from decouple import config

# MongoDB connection string .env file se aayegi
MONGODB_URI: str = config("MONGODB_URI")
DATABASE_NAME: str = config("DATABASE_NAME", default="banking")

# JWT settings (Week 2 me use hoga)
SECRET_KEY: str = config("SECRET_KEY", default="change-this-secret-key")
ALGORITHM: str = config("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=60, cast=int)

# Yeh secret sirf admin bante waqt chahiye - .env me set karo, kisi ko mat batao
ADMIN_CREATION_SECRET: str = config("ADMIN_CREATION_SECRET", default="super-secret-admin-key")
