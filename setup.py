from setuptools import setup

setup(
    name='Table_Tracker',
    packages=['Table_Tracker'],
    include_package_data=True,
    install_requires=[
        'flask', 'flask_socketio', 'firebase_admin', 'random', 'time', 'secrets'
    ],
)




