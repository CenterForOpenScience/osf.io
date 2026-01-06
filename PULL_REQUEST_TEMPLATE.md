[//]: # (
    * Before submitting your Pull Request, make sure you've picked the right branch and your code is up-to-date with it.
        * For critical hotfixes, select "master" as the target branch.
        * For bugfixes, improvements and new features, select "develop" as the target branch.
        * If your PR is part of a project/team, select project/team's dedicated feature branch as the target.
    * If you have a JIRA ticket, prefix the ticket number [ENG-*****] to the PR title.
)

## Ticket

[//]: # (Link to a JIRA ticket if available.)

* [ENG-*****]()

## Purpose

[//]: # (Briefly describe the purpose of this PR.)

## Changes

[//]: # (Briefly describe or list your changes.)

## Side Effects

[//]: # (Any possible side effects?)

## QE Notes

[//]: # (
    * Any QA testing notes for QE?
        * Make verification statements inspired by your code and what your code touches.
        * What are the areas of risk?
        * Any concerns/considerations/questions that development raised?
    * If you have a JIRA ticket, make sure the ticket also contains the QE notes.
)

## CE Notes

[//]: # (
    * Any server configuration and deployment notes for CE?
        * Is model migration required? Is data migration/backfill/population required?
            * If so, is it reversible? Is there a roll-back plan?
        * Does server settings needs to be updated?
            * If so, have you checked with CE on existing settings for affected servers?
        * Are there any deployment dependencies to other services?
    * If you have a JIRA ticket, make sure the ticket also contains the CE notes.
)

## Documentation

[//]: # (
    * Does any internal or external documentation need to be updated?
        * If the API was versioned, update the developer.osf.io changelog.
        * If changes were made to the API, link the developer.osf.io PR here.
)
