## Purpose

Projects one year of account outcomes for the capital-limited portfolio by
resampling its realised daily returns, and reports the result as a console
summary and a fan chart that a real account could be compared against.

## ADDED Requirements

### Requirement: Projection is built from portfolio daily returns
The projection SHALL be computed only from the daily returns of the
capital-limited portfolio replay. Every chart and summary it produces SHALL
come from those paths. It SHALL NOT compound per-trade returns one after
another.

#### Scenario: Fan chart and summary come from the same paths
- **WHEN** the backtest pipeline runs with a non-empty set of trades
- **THEN** the percentile paths drawn in the fan chart come from the same
  simulated portfolio paths as the summary's final-equity percentiles
- **AND** the fan chart's 50th-percentile path ends at the summary's median
  final equity

#### Scenario: Too little history
- **WHEN** the portfolio has fewer than 60 finite daily returns
- **THEN** no projection, summary or fan chart is produced
- **AND** a warning says the Monte Carlo was skipped for too little history
- **AND** the rest of the pipeline continues

### Requirement: Console summary
When a projection is produced, the pipeline SHALL print a summary that gives:
- the number of simulated paths, the horizon in trading days, the bootstrap
  block length and the number of observed daily returns;
- the 5th, 50th and 95th percentile final equity in rupees, each with its %
  change from starting capital;
- the mean maximum drawdown;
- the drawdown exceeded in only the worst 5% of paths, labelled as the
  worst-5% drawdown;
- the % of paths that end above starting capital.

The summary SHALL NOT fail for any projection result the pipeline produces.

#### Scenario: Summary prints for a normal run
- **WHEN** the backtest pipeline produces a projection
- **THEN** the console shows the Monte Carlo summary with every figure above
- **AND** no `[WARN]` about the Monte Carlo is printed

#### Scenario: Worst-tail drawdown is the severe tail
- **WHEN** the summary prints the worst-5% drawdown
- **THEN** that value is less than or equal to the mean maximum drawdown
  (drawdowns are negative)

### Requirement: Fan chart in account terms
When a projection is produced, the pipeline SHALL save a fan chart with:
- trading days ahead on the x-axis, from 0 to the horizon;
- account equity in rupees on the y-axis;
- the 50th-percentile path, and a band between the 5th and 95th percentile
  paths;
- a reference line at starting capital.

All paths SHALL start at starting capital on day 0. At every day the 5th
percentile SHALL be at or below the 50th, and the 50th at or below the 95th.

#### Scenario: Chart starts at starting capital
- **WHEN** the fan chart is drawn for a run with starting capital Rs 10,00,000
- **THEN** all three paths equal Rs 10,00,000 at day 0
- **AND** the reference line is at Rs 10,00,000

#### Scenario: Chart is drawn even if the summary fails
- **WHEN** printing the summary raises an error
- **THEN** the error is reported as a warning
- **AND** the fan chart is still saved

### Requirement: Reproducible projection
With the same daily returns, horizon, path count, block length and seed, the
projection SHALL give identical summary figures and identical percentile
paths on every run. Adding the percentile paths SHALL NOT change the summary
figures the projection produced before this change for the same inputs.

#### Scenario: Same inputs, same outputs
- **WHEN** the projection runs twice on the same inputs and seed
- **THEN** every summary figure and every percentile path is identical

#### Scenario: Existing figures unchanged
- **WHEN** the projection runs on a fixed reference series with seed 42
- **THEN** its median, 5th and 95th percentile final equity, mean maximum
  drawdown, worst-5% drawdown and % profitable paths match the values the
  pre-change code gives for the same series
