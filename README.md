# Stackexchange-Parsing

## Original Job Description

> ### Context:
> Download/parse the pages from Stackexchange (http://www.stackexchange.com) 
> Scrape only the title, date of post, and link (no ads, no sidebar, or other superfluous info) from various Stackexchange communities. A list of communities will be provided by a spreadsheet (format to be given when contract is accepted. 
> 
> ### Deliverables:
> Code. A downloader/parser, written in Python, that can parse the website and pull website content into well-formed JSON files. Code should be well-written, DRY, and follow Google’s Python-styling guide (https://google.github.io/styleguide/pyguide.html).  If you do another job for me, you should be able to reuse portions of this code.
> Files. One well-formed JSON for each Question and Answer.
> Tests. Do test - driven development and include reasonable tests to show that the code works.
> Logs. Write successful files out to a folder (in the same directory as the program is executed) called “stackexchange_jsons”, and failures out to “stackexchange_issues”.  
> On failure, log the failure and the issue in a dated log file; allow program to continue to run.  So every failure has a line in the log corresponding to the file in the failures folder.  Each log line should have the url to the article, and the reason for the failure.
> 
> ### Milestones:
> 1.   Provide 10 or more well-formed JSONs*  from one community
> 2.   Provide 10 or more well-formed JSONs* from multiple communities.
> 3.  Write to your S3 bucket. Use the default config in logged-in-user’s .aws credentials and .config files.
> 4.   Multi-threaded program: the program should be able to accept, as a command-line argument, the number of processes to use.  Ensure that the operator of the code can exit out of the program (i.e. if ctrl+c continually ends the running process, provide another key command to exit the program)
> 
> * Format to be given. (10 JSONs is a representation of the program’s ability to completely parse the pages and produce all the JSONs correlated with the Stackexchange Q&A posts; these JSONs will be examined for quality.) 
