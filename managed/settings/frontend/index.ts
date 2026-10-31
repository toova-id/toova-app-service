import "./styles.css";
import "./views";
import { registerClientAction } from "@toova/features/feature-registry";
import SettingsShell from "@toova/features/settings/settings-shell";
import { registerActionFormView, registerActionListView } from "@toova/views/view-registry";
import { UserSettingsForm } from "./settings-forms";
import RoleSettingsForm from "./role-form";
import { registerSettingsSection } from "@toova/features/settings/settings-registry";
import GeneralSettings from "./general-settings";
import { RolesSettingsList, UsersSettingsList } from "./settings-list";

registerSettingsSection("general", GeneralSettings);
registerClientAction("managed.settings", SettingsShell);
registerActionListView("settings.action_users", UsersSettingsList);
registerActionListView("settings.action_roles", RolesSettingsList);
registerActionFormView("settings.action_users", UserSettingsForm);
registerActionFormView("settings.action_roles", RoleSettingsForm);
