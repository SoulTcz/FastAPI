# app/core/config.py
# Yaha hum saari environment settings ek jagah define karte hain
# taaki poore project me bar bar os.environ.get() na likhna pade

from decouple import config

# MongoDB connection string .env file se aayegi
MONGODB_URI: str = config("MONGODB_URI")
<<<<<<< HEAD
DATABASE_NAME: str = config("DATABASE_NAME", default="banking")
=======
DATABASE_NAME: str = config("DATABASE_NAME", default="baking_ecommerce")
>>>>>>> eb2793f (upload process)

# JWT settings (Week 2 me use hoga)
SECRET_KEY: str = config("SECRET_KEY", default="change-this-secret-key")
ALGORITHM: str = config("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=60, cast=int)

# Yeh secret sirf admin bante waqt chahiye - .env me set karo, kisi ko mat batao
ADMIN_CREATION_SECRET: str = config("ADMIN_CREATION_SECRET", default="super-secret-admin-key")
<<<<<<< HEAD
=======

# Week 4: File upload settings
UPLOAD_FOLDER: str = config("UPLOAD_FOLDER", default="uploads")
MAX_FILE_SIZE: int = config("MAX_FILE_SIZE", default=5 * 1024 * 1024, cast=int)  # 5MB
ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}
>>>>>>> eb2793f (upload process)
