class Config:
    TESTING = False
    DEBUG = False
    DATABASE_URI = 'mysql://root:@localhost/ServiceA'

class TestConfig(Config):
    TESTING = True
    DATABASE_URI = 'mysql://root:@localhost/test_ServiceA'