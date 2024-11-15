#!/usr/bin/env python3.12

import argparse
import actions


def getArgs():
	"""
	Get the command line arguments passed by the user. The return of this can be used to call the function relevant to the subparser "selected" by the user.

	Returns
	-------
		args (argparse.Namespace) : a Namespace object with the parsed arguments

	Example Usage
	-------------
	```
	args = getArgs()
	args.func(args)  # call subparser defaults
	```
	"""
	# dynamically fetch available stacks and services available to control
	stackChoices = actions.getStacksInDir()

	serviceChoices: list[str] = []
	for stack in stackChoices:
		serviceChoices += actions.getServicesInStack(stack)
	serviceChoices = list(set(serviceChoices))
	

	parser = argparse.ArgumentParser(description="Helpful script to manage a group's Gunicorn and PostgreSQL deployment for CSCI 258.", epilog="Author: Noah S. Roberts, 2024")

	subparsers = parser.add_subparsers(required=True, metavar='action')


	# ----------
	# commands used for controlling the container's state
	# ----------
	h = "Starts the specified stack."
	parser_start = subparsers.add_parser('start', description=h, help=h)
	parser_start.add_argument('stack', choices=stackChoices)
	parser_start.set_defaults(func=actions.start)

	h = "Stops the specified stack."
	parser_stop = subparsers.add_parser('stop', description=h, help=h)
	parser_stop.add_argument('stack', choices=stackChoices)
	parser_stop.set_defaults(func=actions.stop)

	h = "Displays the current status of the specified stack."
	parser_status = subparsers.add_parser('status', description=h, help=h)
	parser_status.add_argument('-j', dest='asJson', action='store_true', help='Output status as JSON data')
	# parser_status.add_argument('-r', dest='asRaw', metavar='', help='Output status ')
	parser_status.add_argument('stack', choices=stackChoices)
	parser_status.set_defaults(func=actions.status)

	h = "Build the Docker image(s) used in the stack."
	parser_build = subparsers.add_parser('build', description=h, help=h)
	parser_build.add_argument('stack', choices=stackChoices)
	parser_build.add_argument('service', choices=serviceChoices, nargs='?')
	parser_build.set_defaults(func=actions.build)

	# ----------
	# commands used for executing commands in the container
	# ----------
	h = "Runs the specified command in the given stack and container."
	parser_exec = subparsers.add_parser('exec', description=h, help=h)
	parser_exec.add_argument('stack', choices=stackChoices)
	parser_exec.add_argument('service', choices=serviceChoices)
	parser_exec.add_argument('command', nargs=1)
	parser_exec.add_argument('subargs', nargs='*')
	parser_exec.set_defaults(func=actions.execute)

	h = "Run manage.py with the specified arguments."
	parser_manage = subparsers.add_parser('manage', description=h, help=h)
	parser_manage.add_argument('subargs', nargs='*')
	parser_manage.set_defaults(func=actions.manage)

	# ----------
	# other miscellaneous commands
	# ----------
	h = "Prepare your group's folder for deployment. Parameters can optionally be passed directly from the command line, if desired."
	parser_prep = subparsers.add_parser('prep', description=h, help=h)
	parser_prep.add_argument('-r', dest='gitRepo', metavar='repo_url', help="Remote Git repo url to your Django site.")
	parser_prep.add_argument('-g', dest='groupName', metavar='group_name', help="Name of your group. Should be the name of this folder.")
	parser_prep.add_argument('-s', dest='siteName', metavar='site_name', help="Name of your site. Will be in the URL.")
	parser_prep.add_argument('-p', dest='pfName', metavar='project_folder', help="Name of the Django project folder, ex: django_project, dj.")
	parser_prep.add_argument('-y', dest='alwaysConfirm', action='store_true', help='Answer yes to all confirmation prompts.')
	parser_prep.set_defaults(func=actions.prep)

	h = "Display log output of the stack or one of its services."
	parser_logs = subparsers.add_parser('logs', description=h, help=h)
	parser_logs.add_argument('-f', '--follow', dest='follow', help="Follow log output", action='store_true')
	parser_logs.add_argument('stack', choices=stackChoices)
	parser_logs.add_argument('service', choices=serviceChoices, nargs='?')
	parser_logs.set_defaults(func=actions.logs)

	return parser.parse_args()



def main(args: argparse.Namespace):
	try:
		args.func(args)
	except KeyboardInterrupt:
		exit(1)


if __name__ == '__main__':
	# collect the command line arguments
	args = getArgs()
	main(args)
