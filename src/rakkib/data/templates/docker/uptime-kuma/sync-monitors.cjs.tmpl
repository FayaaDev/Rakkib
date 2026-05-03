const fs = require("fs");
const { io } = require("socket.io-client");

const CONFIG_PATH = process.env.RAKKIB_MONITORS_FILE || "/app/data/rakkib-monitors.json";
const SERVER_URL = process.env.RAKKIB_UPTIME_KUMA_URL || "http://127.0.0.1:3001";

const monitorDefaults = {
    type: "http",
    name: "",
    parent: null,
    url: "https://",
    method: "GET",
    protocol: null,
    location: "world",
    ipFamily: null,
    interval: 60,
    retryInterval: 60,
    resendInterval: 0,
    maxretries: 0,
    retryOnlyOnStatusCodeFailure: false,
    notificationIDList: {},
    ignoreTls: false,
    upsideDown: false,
    expiryNotification: false,
    domainExpiryNotification: false,
    maxredirects: 10,
    accepted_statuscodes: ["200-299"],
    saveResponse: false,
    saveErrorResponse: true,
    responseMaxLength: 1024,
    dns_resolve_type: "A",
    dns_resolve_server: "",
    docker_container: "",
    docker_host: null,
    proxyId: null,
    basic_auth_user: "",
    basic_auth_pass: "",
    mqttUsername: "",
    mqttPassword: "",
    mqttTopic: "",
    mqttWebsocketPath: "",
    mqttSuccessMessage: "",
    mqttCheckType: "keyword",
    authMethod: null,
    oauth_auth_method: "client_secret_basic",
    httpBodyEncoding: "json",
    kafkaProducerBrokers: [],
    kafkaProducerSaslOptions: {
        mechanism: "None",
    },
    cacheBust: false,
    kafkaProducerSsl: false,
    kafkaProducerAllowAutoTopicCreation: false,
    gamedigGivenPortOnly: true,
    remote_browser: null,
    rabbitmqNodes: [],
    rabbitmqUsername: "",
    rabbitmqPassword: "",
    conditions: [],
    system_service_name: "",
};

function loadConfig() {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
}

function emitAck(socket, event, ...args) {
    return new Promise((resolve, reject) => {
        socket.emit(event, ...args, (response) => {
            if (response && response.ok === false) {
                reject(new Error(response.msg || `Socket event failed: ${event}`));
                return;
            }
            resolve(response === undefined ? {} : response);
        });
    });
}

function waitForEvent(socket, event, emitFn) {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            socket.off(event, onEvent);
            reject(new Error(`Timed out waiting for ${event}`));
        }, 15000);

        const onEvent = (payload) => {
            clearTimeout(timeout);
            resolve(payload);
        };

        socket.once(event, onEvent);
        Promise.resolve()
            .then(emitFn)
            .catch((error) => {
                clearTimeout(timeout);
                socket.off(event, onEvent);
                reject(error);
            });
    });
}

function managedDescription(prefix, serviceId) {
    return `${prefix}${serviceId})`;
}

function parseManagedServiceId(prefix, description) {
    if (typeof description !== "string" || !description.startsWith(prefix) || !description.endsWith(")")) {
        return null;
    }
    return description.slice(prefix.length, -1);
}

function buildMonitorPayload(spec, prefix, existing = null) {
    const payload = existing ? { ...existing } : { ...monitorDefaults };
    payload.name = spec.name;
    payload.description = managedDescription(prefix, spec.service_id);
    payload.interval = spec.interval;
    payload.retryInterval = spec.interval;
    payload.maxretries = spec.maxretries;
    payload.timeout = spec.timeout;
    payload.notificationIDList = existing?.notificationIDList || {};
    payload.accepted_statuscodes = existing?.accepted_statuscodes || ["200-299"];
    payload.active = true;

    if (spec.type === "tcp") {
        payload.type = "tcp";
        payload.hostname = spec.hostname;
        payload.port = spec.port;
        payload.url = "";
    } else if (spec.type === "ping") {
        payload.type = "ping";
        payload.hostname = spec.hostname;
        payload.url = "";
    } else {
        payload.type = "http";
        payload.method = "GET";
        payload.url = spec.url;
        payload.ignoreTls = false;
    }

    return payload;
}

async function syncMonitors() {
    const config = loadConfig();
    if (!config.admin || !config.admin.password) {
        throw new Error("Missing Uptime Kuma admin credentials in rakkib-monitors.json");
    }

    const socket = io(SERVER_URL, {
        transports: ["websocket"],
        reconnection: false,
    });

    await new Promise((resolve, reject) => {
        socket.once("connect", resolve);
        socket.once("connect_error", reject);
    });

    try {
        const needsSetup = await emitAck(socket, "needSetup");
        if (needsSetup === true) {
            await emitAck(socket, "setup", config.admin.username, config.admin.password);
        }

        await emitAck(socket, "login", {
            username: config.admin.username,
            password: config.admin.password,
        });

        const currentList = await waitForEvent(socket, "monitorList", () => emitAck(socket, "getMonitorList"));
        const currentManaged = new Map();
        for (const monitor of Object.values(currentList)) {
            const serviceId = parseManagedServiceId(config.managed_prefix, monitor.description);
            if (serviceId) {
                currentManaged.set(serviceId, monitor);
            }
        }

        const desiredIds = new Set(config.monitors.map((monitor) => monitor.service_id));

        for (const [serviceId, monitor] of currentManaged.entries()) {
            if (!desiredIds.has(serviceId)) {
                await emitAck(socket, "deleteMonitor", monitor.id, false);
            }
        }

        for (const spec of config.monitors) {
            const existing = currentManaged.get(spec.service_id) || null;
            const payload = buildMonitorPayload(spec, config.managed_prefix, existing);
            if (existing) {
                payload.id = existing.id;
                await emitAck(socket, "editMonitor", payload);
            } else {
                await emitAck(socket, "add", payload);
            }
        }
    } finally {
        socket.close();
    }
}

syncMonitors().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
});
