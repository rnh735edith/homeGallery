import { useState } from "react";

export default function StepNotifications({ config, updateConfig }) {
  const notif = config.notifications || {
    enabled: false,
    bot_token: "",
    chat_id: "",
  };

  const [showToken, setShowToken] = useState(false);

  return (
    <div className="setup-step">
      <h2>Telegram Notifications</h2>
      <p className="setup-description">
        Optional: Receive server alerts via Telegram (startup, errors, security
        events). You can configure this later in Settings.
      </p>

      <div className="form-group">
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={notif.enabled}
            onChange={(e) =>
              updateConfig("notifications", { enabled: e.target.checked })
            }
          />
          Enable Telegram Notifications
        </label>
      </div>

      {notif.enabled && (
        <>
          <div className="form-group">
            <label>Bot Token</label>
            <input
              type={showToken ? "text" : "password"}
              value={notif.bot_token}
              onChange={(e) =>
                updateConfig("notifications", { bot_token: e.target.value })
              }
              placeholder="123456:ABC-DEF..."
            />
            <small>
              Get from{" "}
              <a href="https://t.me/BotFather" target="_blank" rel="noreferrer">
                @BotFather
              </a>{" "}
              on Telegram
            </small>
          </div>

          <div className="form-group">
            <label>Chat ID</label>
            <input
              type="text"
              value={notif.chat_id}
              onChange={(e) =>
                updateConfig("notifications", { chat_id: e.target.value })
              }
              placeholder="503968467"
            />
            <small>
              Get from{" "}
              <a
                href="https://t.me/userinfobot"
                target="_blank"
                rel="noreferrer"
              >
                @userinfobot
              </a>{" "}
              on Telegram
            </small>
          </div>

          <div className="form-group">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={showToken}
                onChange={(e) => setShowToken(e.target.checked)}
              />
              Show token
            </label>
          </div>
        </>
      )}
    </div>
  );
}
