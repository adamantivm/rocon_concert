#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_concert/license/LICENSE
#
##############################################################################
# Imports
##############################################################################

import os
import time
import genpy
import rospy
import rocon_python_utils
import yaml
import concert_msgs.msg as concert_msgs
import rocon_std_msgs.msg as rocon_std_msgs
import unique_id

from .exceptions import NoConfigurationUpdateException

##############################################################################
# ServiceList
##############################################################################


def load_service_profiles(service_configuration):
    """
    Scan the package path looking for service exports and grab the ones
    we are interested in and load their service profiles.

    We skip over any services that were configured but not found and just
    provide a ros warning.

    @param service_resource_names : list of services in resource name ('pkg/name') format (name has no extension)
    @type list of str

    @return the loaded service descriptions.
    @rtype { service_name : concert_msgs.ConcertService }
    """
    services_conf = load_service_configuration(service_configuration)  # list of (service, override) resource name tuples
    services_path, _invalid_service_path = rocon_python_utils.ros.resource_index_from_package_exports(rocon_std_msgs.Strings.TAG_SERVICE)

    # filter the not found resources
    found_service_resources = [(r, s) for r, s in services_conf if r in services_path.keys()]
    not_found_services = [r for r, unused_s in services_conf if r not in services_path.keys()]
    if not_found_services:
        rospy.logwarn("Service Manager : some services were not found on the package path %s" % not_found_services)

    # load the service profiles
    service_profiles = {}
    for resource_name, override in found_service_resources:
        filename = services_path[resource_name]
        with open(filename) as f:
            service_profile = concert_msgs.ConcertService()
            service_yaml = yaml.load(f)
            service_yaml['resource_name'] = resource_name

            if override:
                # override
                override_parameters(service_yaml, override)

            # replace icon resource name to real icon
            if 'icon' in service_yaml:
                replace = {}
                replace[service_yaml['icon']] = rocon_python_utils.ros.icon_resource_to_msg(service_yaml['icon'])
                genpy.message.fill_message_args(service_profile, service_yaml, replace)
            else:
                genpy.message.fill_message_args(service_profile, service_yaml)

            # Validation
            if service_profile.launcher_type == '':  # not set
                service_profile.launcher_type = concert_msgs.ConcertService.TYPE_SHADOW
            if service_profile.launcher_type != concert_msgs.ConcertService.TYPE_ROSLAUNCH and \
               service_profile.launcher_type != concert_msgs.ConcertService.TYPE_SHADOW and \
               service_profile.launcher_type != concert_msgs.ConcertService.TYPE_CUSTOM:
                rospy.logwarn("Service Manager : invalid service launcher type [%s]" % (filename))
                continue
            # Fill in missing fields or modify correctly some values
            service_profile.uuid = unique_id.toMsg(unique_id.fromRandom())
            # We need to make sure the service description name is a valid rosgraph namespace name
            # @todo Actually call the rosgraph function to validate this (do they have converters?)
            service_profile.name = service_profile.name.lower().replace(" ", "_")
            if service_profile.name in service_profiles.keys():
                rospy.logwarn("Service Manager : service description with this name already present, not adding [%s]" % service_profile.name)
            else:
                service_profiles[service_profile.name] = service_profile

    rospy.loginfo("Service Manager : Solution Configuration has been updated")
    return service_profiles

# LAST_CONFIG_LOADED = None
# 
# 
# def load_service_configuration(resource_name):
#     '''
#         Loads service configuration file
# 
#         :param resource_name: yaml file listing services to load (e.g concert_tutorial/tutorial.services)
#         :type resource_name: str
#     '''
#     filepath = rocon_python_utils.ros.find_resource_from_string(resource_name)
#     modified_time = time.ctime(os.path.getmtime(filepath))
#     global LAST_CONFIG_LOADED
# 
#     if LAST_CONFIG_LOADED:
#         if modified_time == LAST_CONFIG_LOADED:
#             raise NoConfigurationUpdateException("It is up-to-date")
# 
#     LAST_CONFIG_LOADED = modified_time
#     services = []
#     with open(filepath) as f:
#         services_yaml = yaml.load(f)
# 
#         for s in services_yaml:
#             r = s['resource_name']
#             o = s['override'] if 'override' in s else None
#             services.append((r, o))
#     return services


def override_parameters(yaml, override):
    for key in yaml:
        if key in override:
            yaml[key] = override[key]
