{{/* Chart-standard naming and labels. */}}

{{- define "pgbouncer-manager.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "pgbouncer-manager.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "pgbouncer-manager.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "pgbouncer-manager.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "pgbouncer-manager.operatorSelectorLabels" -}}
app.kubernetes.io/name: {{ include "pgbouncer-manager.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: operator
{{- end -}}

{{- define "pgbouncer-manager.managerSelectorLabels" -}}
app.kubernetes.io/name: {{ include "pgbouncer-manager.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: manager
{{- end -}}

{{- define "pgbouncer-manager.serviceAccountName" -}}
{{- if .Values.operator.serviceAccount.create -}}
{{- default (printf "%s-operator" (include "pgbouncer-manager.fullname" .)) .Values.operator.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.operator.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* The manager image, defaulting its tag to the chart's appVersion so a chart
     upgrade moves the image with it. */}}
{{- define "pgbouncer-manager.image" -}}
{{- printf "%s:%s" .Values.operator.image.repository (default .Chart.AppVersion .Values.operator.image.tag) -}}
{{- end -}}

{{- define "pgbouncer-manager.poolerName" -}}
{{- default (include "pgbouncer-manager.fullname" .) .Values.pooler.name -}}
{{- end -}}
