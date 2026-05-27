## ADDED Requirements

### Requirement: Surface robustness status in phenotype reporting
The system SHALL expose robustness-stage conclusions in the run-specific phenotype reporting outputs so the main narrative can distinguish robustness-supported findings from exploratory, artifact-risk, or threshold-sensitive findings.

#### Scenario: Reporting artifacts incorporate robustness classifications
- **WHEN** a run contains completed coupling-robustness outputs
- **THEN** the reporting layer includes the robustness status and source artifact reference for each tracked AC/NF headline finding
- **AND** the primary main-cohort narrative does not present an exploratory or artifact-risk finding as if it were robustness-supported

#### Scenario: Reporting degrades gracefully when robustness outputs are absent
- **WHEN** a user rerenders reporting for a run that does not contain the coupling-robustness stage
- **THEN** the reporting layer records that robustness classification is unavailable
- **AND** the rerender still succeeds without fabricating robustness labels
