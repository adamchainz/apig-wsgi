Example Application
===================

Requirements
------------

Python 3.9.

The Application
---------------

The application in ``app/`` is a simple database-less Django application with
debugging pages.

(Optional) Runnning the Application Locally
-------------------------------------------

We use vanilla venv, pip, and Django to run:

.. code-block:: sh

   cd app
   python -m venv venv
   source venv/bin/activate
   python -m pip install -U pip wheel
   python -m pip install -r requirements.txt
   python -m pip install -e ../..
   python manage.py runserver

Open it at http://127.0.0.1:8000/

Deploying the Application
-------------------------

Best done in a separate terminal session, since there’s a second venv.

First, set yourself up to use the AWS account you want. This can be done by
configuring the AWS CLI in the usual way.

After you’ve done that, create a deployment venv, install Ansible and
other requirements into it, and run the deployment playbook:

.. code-block:: sh

   cd deployment
   python -m venv venv
   source venv/bin/activate
   python -m pip install -U pip wheel
   python -m pip install -r requirements.txt
   ansible-playbook playbook.yml

Ansible will build the application and deploy it to the `eu-central-1` region
(this can be changed in the plyabook).

The playbook run should complete with a ``PLAY RECAP`` at the end like:

.. code-block:: sh

   PLAY RECAP ********************************************************************
   localhost                  : ok=12   changed=8    unreachable=0    failed=0

Check that ``failed=0`` - if not, see the preceding output for error
messages.

Also in the output there is a final ``debug`` task displaying the URL’s
of the deployments. Open them in a web browser to check them out!

If you want to test the ALB deployment as well, you’ll need to provide some
extra variables: the ID of the VPC and two subnets to create the ALB in.
These can be retrieved from `the VPC console
<https://eu-central-1.console.aws.amazon.com/vpc/home?region=eu-central-1#subnets:>`__.

Pass them in like:

.. code-block:: sh

   ansible-playbook playbook.yml -e vpc_id=vpc-12345678 -e subnet_id_1=subnet-12345678 -e subnet_id_2=subnet-12345678

You can delete the ALB by re-running the playbook without those parameters
defined.

To Clean Up
-----------

The playbook creates two CloudFormation stacks prefixed with 'apig-wsgi', by
default in the eu-central-1 region. You can see these on `the CloudFormation
console <https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks>`__.

To clean up, first delete the site stack, then delete the base
stack (which will require manual removal of the files in the S3 bucket).
