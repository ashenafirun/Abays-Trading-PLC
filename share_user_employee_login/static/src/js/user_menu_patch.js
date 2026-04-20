import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

import { session } from "@web/session";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        this.employee_id_login = session.employee_id_login;
        this.employee_avatar = session.employee_avatar;
        this.employee_name = session.employee_name;
    },
});
