from distutils.core import setup

setup(
    name='cloudify-3.2-snapshot',
    version='1.0.0',
    packages=['cloudify_32_snapshot'],
    install_requires=[],
    keywords='cloudify 3.2 snapshots',
    author='Marcin Wasilewski and Konrad Paziewski',
    description='Utility to create snapshots on Cloudify manager 3.2',
    entry_points={
        'console_scripts': [
            'cfy-snapshot32=cloudify_32_snapshot:main',
        ],
    },
)
