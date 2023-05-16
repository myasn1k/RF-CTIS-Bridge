# RF-CTIS-bridge

Synchronize Recorded Future alerts and alert rules with CTIS modelling a tree-like structure connecting customers, services, categories, alert rules and alerts.

## Configuration

In `config_vol/`, please copy `config.sample.yaml` to `config.yaml`, and add the following:

* Slack url (API hook): error and info notifications.
* CTIS:
  * url: ctis endpoint
  * username
  * password
* Recorded Future token (connect API)
* Mappings (see config template for further info)

## Usage

This is intended to be run in Docker via a cronjob on whatever increment you decide to use.

First, build the container: `docker-compose build app`

Then, add it to your crontab. Example crontab entry:

```
*/30 * * * * cd /PATH/TO/RF-CTIS-bridge && ./run.sh
```
