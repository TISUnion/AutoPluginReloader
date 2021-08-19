**English** | [中文](readme_cn.md)

Auto Plugin Reloader
-----

A MCDReforged (>=2.x) plugin

Automatically trigger plugin reloading when any plugin file (files with extension `.py` and `.mcdr` in plugin directories) changes

## Config

Configure file: `config/auto_plugin_reloader/config.json`

`enabled`, if the reloader is enabled, default: `true`

`permission`, the minimum permission level to use the command, default: `4`

`detection_interval_sec`, the time interval between file change detections in seconds, default: `20`

`reload_delay_sec`, the time delay after file changes detected and before plugin reload gets triggered in seconds, default: `1`

`blacklist`, a list of string, contains name of files in the plugin directories that will be ignored by this plugin

## Command

`!!apr`: Display help message

`!!apr status`: Display the status of the reloader

`!!apr enable`: Enabled the reloader

`!!apr disable`: Disabled the reloader

`!!apr set_interval <interval_sec>`: Set the detection interval, unit: seconds
