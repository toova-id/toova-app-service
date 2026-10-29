import { registerActionView } from "@toova/views/view-metadata";

registerActionView("people.action_employees", {
  list: { columns: ["name", "job_id", "department_id", "work_email", "work_phone"] },
  form: { titleField: "name", sections: [
    { id: "work", label: "Informasi pekerjaan", columns: 2, fields: ["image_1920", "name", "job_id", "department_id", "parent_id", "coach_id", "work_location_id", "work_email", "work_phone", "mobile_phone", "user_id"] },
    { id: "private", label: "Informasi pribadi", columns: 2, fields: ["address_home_id", "private_email", "phone", "identification_id", "passport_id", "birthday", "gender", "marital"] },
    { id: "emergency", label: "Darurat dan pembayaran", columns: 2, fields: ["emergency_contact", "emergency_phone", "bank_account_id"] },
    { id: "other", label: "Lainnya", columns: 2, fields: ["barcode", "category_ids", "notes"] },
  ] },
});
