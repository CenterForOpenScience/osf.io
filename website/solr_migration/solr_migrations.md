Solr organizes data into "documents" which can then be search on.

Our Solr schema has 12 main fields:

	id -- this is for our project and users. each project is self contained in one 
	document, and users are similary self contanied in one document
	
	** a note: * denotes a dynamic field in Solr. It means that any combination of 
	characters can be used at the beginning of that field. the majority of our fields
	are dynamic, so that we can append the id of our node to differentiate between
	projects and components
	
	*_title
	*_category 
	*_public
	*_wiki
	*_description
	*_url -- we wont search on url so it is not indexed, but we're keeping it so we cna
	navigate to the project
	*_tags -- this is a multivalued values, meaning that it can have multiple values.
	components can have multiple tags, so this field is multivalued
	*_contributors -- multivalued field. ** note: contributors and users are different 
	ways of capturing the same information. searching contributors returns the projects 
	that the searched for person is part of it. alternatively, searching users returns
	the profile pages of the user **
	*_contributors_url -- not indexed because we wont search on it, but we will keep it
	so we can easily navigate to contributor 
	public -- not dynamic, as we will filter projects that are not public. if a node is
	private, we still want to return the project itself.
	user -- where we can search for the actual user profile pages. we are not storing
	the url because what we need to build the url will is the id of the document. 
	
	
We also have 7 copyFields. copyFields are the fields that our dynamicFields point to

	text -- our main copy field. it also happens to be our default field (so we dont have
	to specify that we are searching that field when we post to solr). this fields has
	multiple sources. They are: *_title, *_tags, *_wiki, *_description, and *_contributors
	
	category -- the source of this is *_category.
	description -- source is *_description
	wiki -- source is *_wiki
	title -- source is *_title
	tags -- source is *_tags
	contributors -- source is *_contributors
	
	