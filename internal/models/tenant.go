package models

type Tenant struct {
	ID       string `json:"id" validate:"required"`
	Host     string `json:"host" validate:"required"`
	Port     int    `json:"port" default:"5432"`
	DBName   string `json:"db_name" default:"postgres"`
	User     string `json:"user" default:"postgres"`
	Password string `json:"password" validate:"required"`
	PoolSize int    `json:"pool_size" default:"15"`
}

type TenantResponse struct {
	ID       string `json:"id"`
	Host     string `json:"host"`
	Port     int    `json:"port"`
	DBName   string `json:"db_name"`
	User     string `json:"user"`
	PoolSize int    `json:"pool_size"`
}

type PoolStatus struct {
	Database  string `json:"database"`
	User      string `json:"user"`
	PoolMode  string `json:"pool_mode"`
	Active    int    `json:"active"`
	Waiting   int    `json:"waiting"`
	Idle      int    `json:"idle"`
	MaxWait   int    `json:"max_wait"`
}

type Stats struct {
	Database     string `json:"database"`
	User         string `json:"user"`
	Type         string `json:"type"`
	State        string `json:"state"`
	Addr         string `json:"addr"`
	Port         int    `json:"port"`
	LocalAddr    string `json:"local_addr"`
	LocalPort    int    `json:"local_port"`
	CreateTime   int64  `json:"create_time"`
	ConnectTime  int64  `json:"connect_time"`
	ReceiveTime  int64  `json:"receive_time"`
	SendTime     int64  `json:"send_time"`
	WriteBytes   int64  `json:"write_bytes"`
	ReadBytes    int64  `json:"read_bytes"`
	State        string `json:"state"`
	Wait         int    `json:"wait"`
	WaitUS       int    `json:"wait_us"`
}
