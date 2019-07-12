// See https://github.com/dialogflow/dialogflow-fulfillment-nodejs
// for Dialogflow fulfillment library docs, samples, and to report issues
'use strict';

const functions = require('firebase-functions');
const {WebhookClient} = require('dialogflow-fulfillment');

//Used for the pubsub
const google = require('googleapis');
const API_VERSION = 'v1';
const DISCOVERY_API = 'https://cloudiot.googleapis.com/$discovery/rest';
const discoveryUrl = `${DISCOVERY_API}?version=${API_VERSION}`;

const colorMap = {
  white: {red: 255, green: 255, blue:255},
  red: {red: 255, green: 0, blue:0},
  green: {red: 0, green: 255, blue:0},
  blue: {red: 0, green: 0, blue:255},
  off:{red: 0, green: 0, blue:0}
}

process.env.DEBUG = 'dialogflow:debug'; // enables lib debugging statements

// Get the client so we can connect to pub/sub
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

function switchOn (color) {
  console.log('switchOn');
  const config = !color || !colorMap[color] ? colorMap.white : colorMap[color];

  const cb = function (client) {
    setDeviceConfig(client, process.env.IOT_DEVICE_NAME, process.env.IOT_DEVICE_REGISTRY,
      process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT,
      process.env.IOT_GCP_REGION, JSON.stringify(config), 0);
  };

  getClient(process.env.GOOGLE_APPLICATION_CREDENTIALS, cb);
}

function switchOff () {
  console.log('switchOff');
  const config = colorMap.off;

  const cb = function (client) {
    setDeviceConfig(client, process.env.IOT_DEVICE_NAME, process.env.IOT_DEVICE_REGISTRY,
      process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT,
      process.env.IOT_GCP_REGION, JSON.stringify(config), 0);
  };

  getClient(process.env.GOOGLE_APPLICATION_CREDENTIALS, cb);
}


exports.dialogflowFirebaseFulfillment = functions.https.onRequest((request, response) => {
  const agent = new WebhookClient({ request, response });
  console.log('Dialogflow Request headers: ' + JSON.stringify(request.headers));
  console.log('Dialogflow Request body: ' + JSON.stringify(request.body));
  const body = request.body;

  function welcome(agent) {
    agent.add(`Welcome to my agent!`);
  }

  function fallback(agent) {
    agent.add(`I didn't understand`);
    agent.add(`I'm sorry, can you try again?`);
  }

   function switchLightsOn(agent) {
     const color = body.queryResult.parameters.color;

     switchOn(color);
     agent.add(`Switching lights on`);
   }

   function switchLightsOff(agent) {
     switchOff();
     agent.add(`Switching lights off`);
   }

  // // Uncomment and edit to make your own Google Assistant intent handler
  // // uncomment `intentMap.set('your intent name here', googleAssistantHandler);`
  // // below to get this function to be run when a Dialogflow intent is matched
  // function googleAssistantHandler(agent) {
  //   let conv = agent.conv(); // Get Actions on Google library conv instance
  //   conv.ask('Hello from the Actions on Google client library!') // Use Actions on Google library
  //   agent.add(conv); // Add Actions on Google library responses to your agent's response
  // }
  // // See https://github.com/dialogflow/dialogflow-fulfillment-nodejs/tree/master/samples/actions-on-google
  // // for a complete Dialogflow fulfillment library Actions on Google client library v2 integration sample

  // Run the proper function handler based on the matched Dialogflow intent name
  let intentMap = new Map();
  intentMap.set('Default Welcome Intent', welcome);
  intentMap.set('Default Fallback Intent', fallback);
  intentMap.set('smarthome.lights.switch.on', switchLightsOn);
  intentMap.set('smarthome.lights.switch.off', switchLightsOff);
  agent.handleRequest(intentMap);
});
