########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


from setuptools import setup

setup(
    name='cloudify-3.2-snapshot',
    version='1.0.5',
    packages=['cloudify_32_snapshot'],
    license='LICENSE',
    keywords='cloudify 3.2 snapshots',
    author='Marcin Wasilewski and Konrad Paziewski',
    description='Utility to create snapshots on Cloudify manager 3.2',
    entry_points={
        'console_scripts': [
            'cfy-snapshot32=cloudify_32_snapshot:main',
        ],
    },
    install_requires=[
        'fabric==1.8.3',
        'cloudify==3.2.1',
        'ujson==1.35'
    ]
)
