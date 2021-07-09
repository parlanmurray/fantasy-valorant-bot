# Recommended Git Workflow
* Make a commit for each cohesive change.
*  **Never** commit broken code to the master branch!
* Take an extra 30 seconds and craft a good commit message with context (see below).
* Avoid *merge commits* (see below). These clutter up the repo history and make it hard to read.
* You are encouraged to do large feature adds or speculative work in your own branch (see below).

---

# Instructions
## Initial Setup
Before contributing, make sure you have git configured properly so that your name is associated with all of your changes. Run

```sh
$ git config --global user.name "First Last"
$ git config --global user.email "your@email.com"
```
Your default editor for commit messages can be configured with

```sh
$ git config --global core.editor vim
```

---
## Cloning a Repository
The first thing we need to do is *clone* the repository.

```sh
$ git clone https://github.com/parlanmurray/fantasy-valorant-bot.git
```
will create a copy of the repository on your local machine. Enter the repository directory and run

```sh
$ git status
```
You should see that you are on branch 'master' and are up to date with the remote repository (origin).

---
## Staging and Committing
Let's say you created new_feature.h with declarations for the functions you need. You can add it to source control with the command

```sh
$ git add new_feature.h
```

This "stages" new_feature.h, meaning the current state of the file has been stored temporarily. You can continue to work in the directory or even on the same file, and when you commit that version of new_feature.h will be saved to version control.

Now let's say you created new_feature.c. You can stage it just like new_feature.h. If there are more files that have been created or modified,

```sh
$ git add .
```
will stage them all. You can always run

```sh
$ git status
```
again to see which files have been created, modified, and staged.

Now you are ready to commit. Committing is when the changes to your working directory that have been staged are finally added to git's version control. You can simply run

```sh
$ git commit
```
and your default editor will pop up and ask for a commit message. See the next section for guidelines on how to craft a good commit message. 

Please note that at this point, your changes exist only in your local copy of the repository. To push them out where others can see them, see the *Pulling and Pushing* section below.

---
## More on good commit messages
[The seven rules of a great git commit message](https://chris.beams.io/posts/git-commit/)
1. Separate subject from body with a blank line
2. Limit the subject line to 50 characters
3. Capitalize the subject line
4. Do not end the subject line with a period
5. Use the imperative mood in the subject line
6. Wrap the body at 72 characters
7. Use the body to explain what and why vs. how

---
## Pulling and Pushing

Now that you have changes, you can push the new branch to the remote repository with

```sh
$ git push origin new_feature
```
This will create a branch called new_feature in the remote repository and push your changes to it. Once a branch exists in the remote and your local branch has been linked to it, you only need to run

```sh
$ git push
```

However, if multiple people are working on the same branch someone might push a commit to the remote before you do. In that case, your push will fail. First you need to

```sh
$ git pull
```
from the remote in order to download the other changes and apply them to your local repository. You can choose to pull before or after you commit. As long as the changes in the remote commits do not apply to files you have modified, pulling before you commit your changes will work. If the same file has been changed, you will need to commit before pulling so that git can merge the remote repository and your own properly (more on merging later).

---
## Avoiding merge commits
**It is best practice to pull every time before you commit if there are other developers working on the same project. Or, just get in the habit of always using _git pull --rebase_ when pulling**. If you don't, and if someone has made commits to the repo since your last pull, you will see something like this when you go to push your changes: 

```sh
$ git push
To ...
 ! [rejected]        master -> master (fetch first)
error: failed to push some refs to '...'
hint: Updates were rejected because the remote contains work that you do
hint: not have locally. This is usually caused by another repository pushing
hint: to the same ref. You may want to first integrate the remote changes
hint: (e.g., 'git pull ...') before pushing again.
hint: See the 'Note about fast-forwards' in 'git push --help' for details.
```
Now, if you do what git says and stop there, you will get the dreaded merge-commit. However, this is easy to fix. Go ahead and make the commit. Then run

```sh
$ git pull --rebase
```
There is no need to commit after this, just go ahead and *push* your changes. If, like me, you just habitually do a pull at the start of your day to see what your teammates have been up to, and if you have unstaged changes, the above will fail with a warning to commit or stash your changes. Stash is also mentioned below in regards to switching branches. The solution:

```sh
$ git stash
$ git pull --rebase
$ git stash apply
``` 

---
## Branching

Now let's say that you want to add a feature called new_feature. Start by creating a branch called new_feature (or whatever you feel is most descriptive) and checking it out.

```sh
$ git branch new_feature   # This creates a branch based on your current working directory
$ git checkout new_feature # Switch from master to your new branch
# Alternatively
$ git checkout -b new_feature
```

Now you can work on this branch and commit changes as you go without worrying about breaking the codebase for someone else.

When it comes to merging your branch back into the master (or another branch) you have two choices: a traditional merge or a rebase. The former preserves branch history, whereas the latter replays the branch history onto the master, thus the final result is a linear history. What to do is some matter of debate, but suffice it to say that small branches should probably be rebased, whereas larger branches tend to be merged traditionally. Details on both follow.

### Switching branches and stashing
If you're in the middle of developing on a branch and you want to switch to a different branch, but don't yet want to commit your changes, the git *stash* command is indicated.

```sh
$ git stash
$ git checkout <branch_name>
```
When you come back to your original branch, use *git stash apply* to recover your in-progress changes.

---
## Merging

You can merge your new_feature branch back into master with

```sh
$ git checkout master
$ git pull # Not strictly needed but a good idea
$ git merge new_feature
```
Now master contains whatever changes you made in your new_feature branch. At this point you should push again so that your changes will be propagated to everyone the next time they pull.

### Merge Conflicts

If your changes happen to conflict with those in another branch that you are trying to merge with git will be unable to fix the conflict on its own. Instead it will say something like `Automatic merge failed; fix conflicts and then commit the result.` You must now fix the commit by editing the problematic file in your favorite editor or merge tool. When you are done, every instance of

```sh
<<<<<< HEAD
...
======
...
>>>>>> <branch to merge>
```
should be replaced with what you want to have after the merge. Complete the merge by adding the file(s) and committing with whatever explanation you feel is appropriate.

One thing to note is that when you `pull` in git, what actually happens is git will `fetch` the data from the remote repository and place it in a branch on the local machine, then attempt to `merge` that branch into your own. Thus fixing pull failures is just like fixing any other merge conflict.

----------

## Rebasing

Staying with the example branch "new_feature":

```
$ git checkout new_feature
$ git rebase master
$ git checkout master
$ git merge new_feature
$ git push
```
Since rebasing linearizes the history in the target branch (e.g. master), it is as if the branch never happened. To keep the number of branches manageable, it is preferable to simply delete the source branch. To delete the branch from both your local copy and the remote repository:

```
$ git branch -D new_feature
$ git push origin --delete new_feature
```
