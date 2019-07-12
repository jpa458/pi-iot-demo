'use strict';

const google = require('googleapis');

const API_VERSION = 'v1';
const DISCOVERY_API = 'https://cloudiot.googleapis.com/$discovery/rest';
const discoveryUrl = `${DISCOVERY_API}?version=${API_VERSION}`;

// From nodejs-docs-samples/iot/manager.js ... with getApplicationDefault creds
function getClient (serviceAccountJson, cb) {
  google.auth.getApplicationDefault(function (err, authClient, projectId) {
    if (err) {
      console.log('Authentication failed because of ', err);
      return;
    }

    google.options({auth: authClient});
    google.discoverAPI(discoveryUrl, {}, (err, client) => {
      if (err) {
        console.log('Error during API discovery', err);
        return undefined;
      }
      cb(client);
    });
  });
}

// From nodejs-docs-samples/iot/manager.js#605...636
function setDeviceConfig (client, deviceId, registryId, projectId,
  cloudRegion, data, version) {
  const parentName = `projects/${projectId}/locations/${cloudRegion}`;
  const registryName = `${parentName}/registries/${registryId}`;

  const binaryData = Buffer.from(data).toString('base64');
  const request = {
    name: `${registryName}/devices/${deviceId}`,
    versionToUpdate: version,
    binaryData: binaryData
  };

  console.log('Set device config.');

  client.projects.locations.registries.devices.modifyCloudToDeviceConfig(
    request,
    (err, data) => {
      if (err) {
        console.log('Could not update config:', deviceId);
        console.log('Message: ', err);
      } else {
        console.log('Success :', data);
      }
    });
}

exports.relayCloudIot = function (event, callback) {
  // [START iot_relay_message_js]
  console.log(event);
  const pubsubMessage = event.data;
  console.log(pubsubMessage);
  const record = JSON.parse(
    pubsubMessage
      ? Buffer.from(pubsubMessage, 'base64').toString()
      : '{}');
  console.log(record);
  const config = {
    red: 0,
    green: 0,
    blue:0
  };

  if (record.button1 ==='1') {
    config.red = 255;
  } else if (record.button2 === '1') {
	config.green = 255;
  }
console.log(config);
  const cb = function (client) {
    setDeviceConfig(client, process.env.IOT_DEVICE_NAME, process.env.IOT_DEVICE_REGISTRY,
      process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT,
      process.env.IOT_GCP_REGION, JSON.stringify(config), 0);
  };

  getClient(process.env.GOOGLE_APPLICATION_CREDENTIALS, cb);
  // [END iot_relay_message_js]
};
