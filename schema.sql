-- Esquema y datos iniciales de la base de datos SQLite del VM Dashboard.
-- No hace falta ejecutarlo: el backend crea vm_dashboard.db con estas tablas y datos al arrancar.
-- Sirve como referencia, o para crear la base a mano con: sqlite3 vm_dashboard.db < schema.sql
-- Las contraseñas están cifradas con bcrypt (admin123 y cliente123).
BEGIN TRANSACTION;
CREATE TABLE users (
	id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	hashed_password VARCHAR(128) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "users" VALUES(1,'admin@vmdashboard.com','Administrador','$2b$12$Hbey0O2vt/UrPDr7lObzL.jSDtuIc3LcinRYyVv0RyzjEp/EAmzmm','Administrador',1,'2026-10-05 13:08:14.624258');
INSERT INTO "users" VALUES(2,'cliente@vmdashboard.com','Cliente demo','$2b$12$WptkM7M5fimLnSIDUhoSheaKmpmcAOhPbLUloDHH72LVstPIVzsOG','Cliente',1,'2026-10-05 13:08:14.624266');
CREATE TABLE vms (
	id INTEGER NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	cores INTEGER NOT NULL, 
	ram INTEGER NOT NULL, 
	disk INTEGER NOT NULL, 
	os VARCHAR(128) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "vms" VALUES(1,'web-01',2,4,80,'Ubuntu 24.04','running','2026-10-05 13:08:14.629425','2026-10-05 13:08:14.629430');
INSERT INTO "vms" VALUES(2,'web-02',2,4,80,'Ubuntu 24.04','running','2026-10-05 13:08:14.629432','2026-10-05 13:08:14.629433');
INSERT INTO "vms" VALUES(3,'api-01',4,8,120,'Debian 12','running','2026-10-05 13:08:14.629434','2026-10-05 13:08:14.629435');
INSERT INTO "vms" VALUES(4,'db-01',8,32,500,'Rocky Linux 9','running','2026-10-05 13:08:14.629437','2026-10-05 13:08:14.629463');
INSERT INTO "vms" VALUES(5,'cache-01',2,16,40,'Debian 12','running','2026-10-05 13:08:14.629465','2026-10-05 13:08:14.629466');
INSERT INTO "vms" VALUES(6,'worker-01',4,8,80,'Ubuntu 22.04','stopped','2026-10-05 13:08:14.629467','2026-10-05 13:08:14.629468');
INSERT INTO "vms" VALUES(7,'monitor-01',2,4,120,'Ubuntu 24.04','running','2026-10-05 13:08:14.629469','2026-10-05 13:08:14.629469');
INSERT INTO "vms" VALUES(8,'backup-01',2,8,1000,'Rocky Linux 9','stopped','2026-10-05 13:08:14.629470','2026-10-05 13:08:14.629471');
INSERT INTO "vms" VALUES(9,'ci-runner-01',8,16,200,'Ubuntu 22.04','paused','2026-10-05 13:08:14.629472','2026-10-05 13:08:14.629473');
INSERT INTO "vms" VALUES(10,'win-app-01',4,16,160,'Windows Server 2022','error','2026-10-05 13:08:14.629473','2026-10-05 13:08:14.629474');
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_vms_status ON vms (status);
CREATE UNIQUE INDEX ix_vms_name ON vms (name);
COMMIT;
