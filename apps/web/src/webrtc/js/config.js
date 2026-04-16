import { getServers } from "./icesettings.js";
import { HTTP_MAP } from "../../constants/config.js";

export async function getServerConfig() {

  const protocolEndPoint = HTTP_MAP["WebrtcConfig"]

  console.log("Config URL:", protocolEndPoint);

  const createResponse =
    await fetch(protocolEndPoint);

  if (!createResponse.ok) {
    throw new Error(
      `Failed config fetch: ${createResponse.status}`
    );
  }

  return await createResponse.json();
}

export function getRTCConfiguration() {
  let config = {};
  config.sdpSemantics = "unified-plan";
  config.iceServers = getServers();
  return config;
}