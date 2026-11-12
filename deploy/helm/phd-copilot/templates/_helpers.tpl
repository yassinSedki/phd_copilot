{{/* Labels shared by every object in the release. */}}
{{- define "phd.labels" -}}
app.kubernetes.io/part-of: phd-copilot
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "phd.backendImage" -}}
{{ .Values.image.backend.repository }}:{{ .Values.image.backend.tag }}
{{- end }}

{{- define "phd.frontendImage" -}}
{{ .Values.image.frontend.repository }}:{{ .Values.image.frontend.tag }}
{{- end }}

{{/* Container hardening shared by all app containers. */}}
{{- define "phd.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop: ["ALL"]
{{- end }}
